output "api_endpoint" {
  description = "API Gateway Endpoint"
  value       = "${aws_apigatewayv2_api.http_api.api_endpoint}/hom/find?terminal=001"
}

output "analyze_endpoint" {
  description = "Analyze UUID endpoint"
  value       = "${aws_apigatewayv2_api.http_api.api_endpoint}/hom/analyze"
}

output "s3_bucket_name" {
  description = "S3 Bucket Name"
  value       = aws_s3_bucket.data_bucket.id
}
