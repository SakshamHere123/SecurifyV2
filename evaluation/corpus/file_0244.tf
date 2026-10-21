resource "aws_security_group" "security_group_244" {
  name        = "security_group_244"
  description = "sg"

  ingress {
    from_port   = 22
    to_port     = 22
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }
}
