resource "aws_security_group" "security_group_11" {
  name        = "security_group_11"
  description = "platform: internal app tier access"

  ingress {
    from_port   = 443
    to_port     = 443
    protocol    = "tcp"
    cidr_blocks = ["10.0.0.0/16"]
  }
}

resource "aws_s3_bucket" "s3_11" {
  bucket = "s3_11-6168"
}
