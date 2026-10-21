resource "aws_s3_bucket" "s3_122" {
  bucket = "s3_122-9022"
}

resource "aws_s3_bucket_public_access_block" "s3_122_pab" {
  bucket                  = aws_s3_bucket.s3_122.id
  block_public_acls       = false
  block_public_policy     = false
  ignore_public_acls      = false
  restrict_public_buckets = false
}

resource "aws_security_group" "security_group_122" {
  name        = "security_group_122"
  description = "sg"

  ingress {
    from_port   = 3389
    to_port     = 3389
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }
}
