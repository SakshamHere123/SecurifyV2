resource "aws_security_group" "security_group_127" {
  name        = "security_group_127"
  description = "sg"

  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }
}
