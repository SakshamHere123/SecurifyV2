resource "aws_security_group" "security_group_304" {
  name        = "security_group_304"
  description = "sg"

  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }
}

resource "aws_s3_bucket" "s3_304" {
  bucket = "s3_304-5009"
}
