resource "aws_iam_role" "iam_7" {
  name = "app-iam_7"
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
