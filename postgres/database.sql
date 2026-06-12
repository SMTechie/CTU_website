DROP TABLE IF EXISTS audit_logs CASCADE;
DROP TABLE IF EXISTS ticket_comments CASCADE;
DROP TABLE IF EXISTS tickets CASCADE;
DROP TABLE IF EXISTS passwords CASCADE;
DROP TABLE IF EXISTS users CASCADE;

CREATE TABLE users (
    user_id INT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    username VARCHAR(50) UNIQUE NOT NULL,
    passwords VARCHAR(255) NOT NULL,
    mfa_enabled BOOLEAN DEFAULT FALSE NOT NULL,
    totp_secret VARCHAR(128) DEFAULT NULL,                         
    account_status VARCHAR(20) DEFAULT 'active' NOT NULL, 
    failed_login_attempts INT DEFAULT 0 NOT NULL,
    last_login_at TIMESTAMP WITH TIME ZONE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP NOT NULL,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP NOT NULL
);

CREATE TABLE passwords (
    password_id INT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    user_id INT REFERENCES users(user_id) ON DELETE CASCADE NOT NULL,
    old_password_hash VARCHAR(255) NOT NULL,
    changed_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP NOT NULL
);

CREATE TABLE tickets (
    id INT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    name VARCHAR(100) NOT NULL,
    email VARCHAR(255) NOT NULL,
    message TEXT NOT NULL,
    status VARCHAR(20) DEFAULT 'New' NOT NULL,
    CONSTRAINT chk_ticket_status CHECK (status IN ('New', 'Assigned', 'In Progress', 'Resolved')), 
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP NOT NULL,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP NOT NULL
);

CREATE TABLE ticket_comments (
    comment_id INT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    ticket_id INT REFERENCES tickets(id) ON DELETE CASCADE NOT NULL,
    comment TEXT NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP NOT NULL
);

CREATE TABLE audit_logs (
    id INT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    username VARCHAR(50) NOT NULL,
    event VARCHAR(100) NOT NULL,
    timestamp TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP NOT NULL
);

INSERT INTO users (username, passwords, mfa_enabled, totp_secret)
VALUES ('admin', 'password123', true, 'JBSWY3DPEHPK3PXP');

CREATE INDEX idx_users_username ON users(username);
CREATE INDEX idx_tickets_email ON tickets(email);
CREATE INDEX idx_tickets_status ON tickets(status);
CREATE INDEX idx_comments_ticket_id ON ticket_comments(ticket_id);