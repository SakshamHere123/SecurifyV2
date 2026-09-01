resource "aws_s3_bucket" "insecure_bucket" {
  bucket = "my-test-bucket-12345"
}

resource "aws_security_group" "open_sg" {
  name        = "wide-open"
  description = "allows everything"

  ingress {
    from_port   = 22
    to_port     = 22
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }
}