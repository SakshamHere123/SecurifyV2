resource "aws_security_group" "security_group_196" {
  name        = "security_group_196"
  description = "sg"

  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }
}
