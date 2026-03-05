variable "aws_region" {
  description = "AWS Region to deploy resources"
  type        = string
  default     = "us-east-1"
}

variable "aws_profile" {
  description = "AWS Profile to use"
  type        = string
  default     = "default"
}

variable "slack_bot_token" {
  description = "Slack Bot User OAuth token (provide via TF_VAR_slack_bot_token)"
  type        = string
  sensitive   = true
}
