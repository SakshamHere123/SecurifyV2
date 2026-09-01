resource "aws_s3_bucket" "insecure_bucket" {
  bucket = "my-test-bucket-12345"
}
resource "aws_security_group" "open_sg" {
  name        = "wide-open"
  description = "allows everything"
  ingress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }
}
