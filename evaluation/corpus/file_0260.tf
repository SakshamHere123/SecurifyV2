resource "aws_s3_bucket" "s3_260" {
  bucket = "s3_260-7453"
}

resource "aws_iam_role" "iam_260" {
  name = "app-iam_260"
  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect    = "Allow"
      Principal = { Service = "ec2.amazonaws.com" }
      Action    = "sts:AssumeRole"
    }]
  })
  tags = { CostCenter = "eng-platform" }
}
