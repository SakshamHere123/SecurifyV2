resource "aws_security_group" "security_group_189" {
  name        = "security_group_189"
  description = "sg"

  ingress {
    from_port   = 22
    to_port     = 22
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }
}

resource "aws_s3_bucket" "s3_189" {
  bucket = "s3_189-9693"
}
