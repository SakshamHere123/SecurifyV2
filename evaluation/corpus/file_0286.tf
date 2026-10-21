resource "aws_s3_bucket" "s3_286" {
  bucket = "s3_286-4027"
}

resource "aws_security_group" "security_group_286" {
  name        = "security_group_286"
  description = "sg"

  ingress {
    from_port   = 22
    to_port     = 22
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }
}
