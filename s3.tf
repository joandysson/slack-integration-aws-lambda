# ---------------------------------------------------------------------------------------------------------------------
# RANDOM SUFFIX FOR S3 BUCKET
# ---------------------------------------------------------------------------------------------------------------------
resource "random_pet" "bucket_suffix" {
  length    = 4
  separator = "-"
}

# ---------------------------------------------------------------------------------------------------------------------
# S3 BUCKET AND OBJECT
# ---------------------------------------------------------------------------------------------------------------------
resource "aws_s3_bucket" "data_bucket" {
  bucket        = "poc-api-lambda-s3-${random_pet.bucket_suffix.id}"
  force_destroy = true
}

resource "aws_s3_object" "data_file" {
  bucket = aws_s3_bucket.data_bucket.id
  key    = "data.json"
  source = "${path.module}/data/data.json"
}
