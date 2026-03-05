# ---------------------------------------------------------------------------------------------------------------------
# API GATEWAY (HTTP API)
# ---------------------------------------------------------------------------------------------------------------------
resource "aws_apigatewayv2_api" "http_api" {
  name          = "terminal-api"
  protocol_type = "HTTP"
}

resource "aws_apigatewayv2_stage" "default" {
  api_id      = aws_apigatewayv2_api.http_api.id
  name        = "hom"
  auto_deploy = true
}

resource "aws_apigatewayv2_integration" "lambda_integration" {
  api_id           = aws_apigatewayv2_api.http_api.id
  integration_type = "AWS_PROXY"

  integration_uri        = aws_lambda_function.terminal_finder.invoke_arn
  integration_method     = "POST"
  payload_format_version = "2.0"
}

resource "aws_apigatewayv2_integration" "analyze_lambda_integration" {
  api_id           = aws_apigatewayv2_api.http_api.id
  integration_type = "AWS_PROXY"

  integration_uri        = aws_lambda_function.hom_analyze.invoke_arn
  integration_method     = "POST"
  payload_format_version = "2.0"
}

resource "aws_apigatewayv2_route" "find_route" {
  api_id    = aws_apigatewayv2_api.http_api.id
  route_key = "GET /find"
  target    = "integrations/${aws_apigatewayv2_integration.lambda_integration.id}"
}

resource "aws_apigatewayv2_route" "analyze_route" {
  api_id    = aws_apigatewayv2_api.http_api.id
  route_key = "POST /analyze"
  target    = "integrations/${aws_apigatewayv2_integration.analyze_lambda_integration.id}"
}

resource "aws_lambda_permission" "api_gw" {
  statement_id  = "AllowExecutionFromAPIGateway"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.terminal_finder.function_name
  principal     = "apigateway.amazonaws.com"

  source_arn = "${aws_apigatewayv2_api.http_api.execution_arn}/*/*"
}

resource "aws_lambda_permission" "api_gw_analyze" {
  statement_id  = "AllowExecutionFromAPIGatewayAnalyze"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.hom_analyze.function_name
  principal     = "apigateway.amazonaws.com"

  source_arn = "${aws_apigatewayv2_api.http_api.execution_arn}/*/*"
}
