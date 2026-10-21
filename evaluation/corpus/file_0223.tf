resource "aws_s3_bucket" "s3_223" {
  bucket = "s3_223-8498"
  server_side_encryption_configuration {
    rule {
      apply_server_side_encryption_by_default {
        sse_algorithm = "aws:kms"
      }
    }
  }
  logging {
    target_bucket = "s3_223-logs-1605"
    target_prefix = "log/"
  }
  tags = {
    Environment = "production"
    CostCenter  = "eng-platform"
  }
}

resource "aws_iam_policy" "iam_223" {
  name = "iam_223"
  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect   = "Allow"
      Action   = "*"
      Resource = "*"
    }]
  })
}
