resource "aws_db_instance" "rds_302" {
  identifier           = "rds_302"
  engine               = "postgres"
  instance_class       = "db.t3.micro"
  allocated_storage    = 20
  storage_encrypted    = true
  skip_final_snapshot  = true
  availability_zone    = "ap-southeast-1a"
}

resource "aws_security_group" "security_group_302" {
  name        = "security_group_302"
  description = "platform: internal app tier access"

  ingress {
    from_port   = 443
    to_port     = 443
    protocol    = "tcp"
    cidr_blocks = ["10.0.0.0/16"]
  }
}
