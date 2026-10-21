resource "aws_iam_role" "iam_281" {
  name = "app-iam_281"
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

resource "aws_s3_bucket" "s3_281" {
  bucket = "s3_281-6489"
}
