CREATE TABLE IF NOT EXISTS hosts
(
  host_id INT NOT NULL AUTO_INCREMENT,
  mac_addr BIGINT UNSIGNED NOT NULL,
  ip_addr INT UNSIGNED NOT NULL,
  name VARCHAR(255),
  email VARCHAR(255),
  status ENUM ('registered', 'blocked'),
  PRIMARY KEY (host_id),
  UNIQUE KEY (mac_addr),
  UNIQUE KEY (ip_addr)
);

CREATE TABLE IF NOT EXISTS log
(
  message_id INT NOT NULL AUTO_INCREMENT,
  time DATETIME NOT NULL,
  message TEXT,
  PRIMARY KEY (message_id)
);

CREATE TABLE IF NOT EXISTS byte_counts
(
  byte_count_id INT NOT NULL AUTO_INCREMENT,
  host_id INT NOT NULL REFERENCES hosts(host_id),
  start_time DATETIME NOT NULL,
  end_time DATETIME,
  incoming INT UNSIGNED,
  outgoing INT UNSIGNED,
  PRIMARY KEY (byte_count_id)
);