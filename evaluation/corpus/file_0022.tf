resource "aws_security_group" "security_group_22" {
  name        = "security_group_22"
  description = "platform: internal app tier access"

  ingress {
    from_port   = 443
    to_port     = 443
    protocol    = "tcp"
    cidr_blocks = ["10.0.0.0/16"]
  }
}

resource "aws_security_group" "security_group_22_2" {
  name        = "security_group_22_2"
  description = "platform: internal app tier access"

  ingress {
    from_port   = 443
    to_port     = 443
    protocol    = "tcp"
    cidr_blocks = ["10.0.0.0/16"]
  }
}

resource "aws_db_instance" "rds_22" {
  identifier           = "rds_22"
  engine               = "postgres"
  instance_class       = "db.t3.micro"
  allocated_storage    = 20
  storage_encrypted    = true
  publicly_accessible  = false
  skip_final_snapshot  = true
  availability_zone    = "us-east-1a"
}
