resource "aws_iam_policy" "iam_234" {
  name = "iam_234"
  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect   = "Allow"
      Action   = "*"
      Resource = "*"
    }]
  })
}

resource "aws_s3_bucket" "s3_234" {
  bucket = "s3_234-9176"
  server_side_encryption_configuration {
    rule {
      apply_server_side_encryption_by_default {
        sse_algorithm = "aws:kms"
      }
    }
  }
  logging {
    target_bucket = "s3_234-logs-9482"
    target_prefix = "log/"
  }
  tags = {
    Environment = "production"
    CostCenter  = "eng-platform"
  }
}
