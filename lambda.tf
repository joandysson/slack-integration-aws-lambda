# ---------------------------------------------------------------------------------------------------------------------
# LAMBDA FUNCTIONS
# ---------------------------------------------------------------------------------------------------------------------
data "archive_file" "lambda_zip" {
  type        = "zip"
  source_file = "${path.module}/lambda/index.py"
  output_path = "${path.module}/lambda/lambda_function.zip"
}

data "archive_file" "analyze_lambda_zip" {
  type        = "zip"
  source_file = "${path.module}/lambda/analyze.py"
  output_path = "${path.module}/lambda/analyze_lambda_function.zip"
}

data "archive_file" "analyze_processor_lambda_zip" {
  type        = "zip"
  source_file = "${path.module}/lambda/analyze_processor.py"
  output_path = "${path.module}/lambda/analyze_processor_lambda_function.zip"
}

resource "aws_lambda_function" "terminal_finder" {
  filename      = data.archive_file.lambda_zip.output_path
  function_name = "terminal_finder_lambda"
  role          = aws_iam_role.terminal_finder_exec.arn
  handler       = "index.handler"
  runtime       = "python3.9"

  source_code_hash = data.archive_file.lambda_zip.output_base64sha256

  environment {
    variables = {
      BUCKET_NAME = aws_s3_bucket.data_bucket.bucket
      FILE_KEY    = aws_s3_object.data_file.key
    }
  }
}

resource "aws_lambda_function" "hom_analyze" {
  filename      = data.archive_file.analyze_lambda_zip.output_path
  function_name = "hom_analyze_lambda"
  role          = aws_iam_role.hom_analyze_exec.arn
  handler       = "analyze.handler"
  runtime       = "python3.9"
  timeout       = 30

  source_code_hash = data.archive_file.analyze_lambda_zip.output_base64sha256

  environment {
    variables = {
      MODEL_ID                = "deepseek.v3.2"
      PROCESSOR_FUNCTION_NAME = aws_lambda_function.hom_analyze_processor.function_name
    }
  }
}

resource "aws_lambda_function" "hom_analyze_processor" {
  filename      = data.archive_file.analyze_processor_lambda_zip.output_path
  function_name = "hom_analyze_processor_lambda"
  role          = aws_iam_role.hom_analyze_processor_exec.arn
  handler       = "analyze_processor.handler"
  runtime       = "python3.9"
  timeout       = 30

  source_code_hash = data.archive_file.analyze_processor_lambda_zip.output_base64sha256

  environment {
    variables = {
      FIND_ENDPOINT_BASE = "https://z2leijvks5.execute-api.us-east-1.amazonaws.com/hom/find"
      SLACK_BOT_TOKEN    = var.slack_bot_token
    }
  }
}

# ---------------------------------------------------------------------------------------------------------------------
# IAM ROLES AND POLICIES FOR EACH LAMBDA
# ---------------------------------------------------------------------------------------------------------------------
resource "aws_iam_role" "terminal_finder_exec" {
  name = "terminal_finder_lambda_role_${random_pet.bucket_suffix.id}"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Action = "sts:AssumeRole"
      Effect = "Allow"
      Principal = {
        Service = "lambda.amazonaws.com"
      }
    }]
  })
}

resource "aws_iam_policy" "terminal_finder_policy" {
  name        = "terminal_finder_lambda_policy_${random_pet.bucket_suffix.id}"
  description = "Least-privilege policy for terminal_finder_lambda"

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Action = [
          "s3:GetObject"
        ]
        Effect   = "Allow"
        Resource = "${aws_s3_bucket.data_bucket.arn}/${aws_s3_object.data_file.key}"
      },
      {
        Action = [
          "logs:CreateLogGroup"
        ]
        Effect   = "Allow"
        Resource = "*"
      },
      {
        Action = [
          "logs:CreateLogStream",
          "logs:PutLogEvents"
        ]
        Effect   = "Allow"
        Resource = "arn:aws:logs:${var.aws_region}:*:log-group:/aws/lambda/terminal_finder_lambda:*"
      }
    ]
  })
}

resource "aws_iam_role_policy_attachment" "terminal_finder_policy_attach" {
  role       = aws_iam_role.terminal_finder_exec.name
  policy_arn = aws_iam_policy.terminal_finder_policy.arn
}

resource "aws_iam_role" "hom_analyze_exec" {
  name = "hom_analyze_lambda_role_${random_pet.bucket_suffix.id}"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Action = "sts:AssumeRole"
      Effect = "Allow"
      Principal = {
        Service = "lambda.amazonaws.com"
      }
    }]
  })
}

resource "aws_iam_policy" "hom_analyze_policy" {
  name        = "hom_analyze_lambda_policy_${random_pet.bucket_suffix.id}"
  description = "Least-privilege policy for hom_analyze_lambda"

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Action = [
          "bedrock:InvokeModel"
        ]
        Effect   = "Allow"
        Resource = "*"
      },
      {
        Action = [
          "lambda:InvokeFunction"
        ]
        Effect   = "Allow"
        Resource = aws_lambda_function.hom_analyze_processor.arn
      },
      {
        Action = [
          "logs:CreateLogGroup"
        ]
        Effect   = "Allow"
        Resource = "*"
      },
      {
        Action = [
          "logs:CreateLogStream",
          "logs:PutLogEvents"
        ]
        Effect   = "Allow"
        Resource = "arn:aws:logs:${var.aws_region}:*:log-group:/aws/lambda/hom_analyze_lambda:*"
      }
    ]
  })
}

resource "aws_iam_role_policy_attachment" "hom_analyze_policy_attach" {
  role       = aws_iam_role.hom_analyze_exec.name
  policy_arn = aws_iam_policy.hom_analyze_policy.arn
}

resource "aws_iam_role" "hom_analyze_processor_exec" {
  name = "hom_analyze_processor_lambda_role_${random_pet.bucket_suffix.id}"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Action = "sts:AssumeRole"
      Effect = "Allow"
      Principal = {
        Service = "lambda.amazonaws.com"
      }
    }]
  })
}

resource "aws_iam_policy" "hom_analyze_processor_policy" {
  name        = "hom_analyze_processor_lambda_policy_${random_pet.bucket_suffix.id}"
  description = "Least-privilege policy for hom_analyze_processor_lambda"

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Action = [
          "logs:CreateLogGroup"
        ]
        Effect   = "Allow"
        Resource = "*"
      },
      {
        Action = [
          "logs:CreateLogStream",
          "logs:PutLogEvents"
        ]
        Effect   = "Allow"
        Resource = "arn:aws:logs:${var.aws_region}:*:log-group:/aws/lambda/hom_analyze_processor_lambda:*"
      }
    ]
  })
}

resource "aws_iam_role_policy_attachment" "hom_analyze_processor_policy_attach" {
  role       = aws_iam_role.hom_analyze_processor_exec.name
  policy_arn = aws_iam_policy.hom_analyze_processor_policy.arn
}
