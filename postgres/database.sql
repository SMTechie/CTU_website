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

INSERT INTO users (username, passwords, mfa_enabled, totp_secret)
VALUES ('admin', 'password123', true, 'JBSWY3DPEHPK3PXP');

CREATE INDEX idx_users_username ON users(username);