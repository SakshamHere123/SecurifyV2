resource "aws_s3_bucket" "s3_5" {
  bucket = "s3_5-6881"
}

resource "aws_iam_role" "iam_5" {
  name = "app-iam_5"
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
