CREATE TABLE IF NOT EXISTS hosts
(
  host_id INT NOT NULL AUTO_INCREMENT,
  mac_addr BIGINT UNSIGNED NOT NULL,
  ip_addr INT UNSIGNED,
  name VARCHAR(255),
  email VARCHAR(255),
  registered BOOL NOT NULL,
  blocked BOOL NOT NULL,
  since DATETIME NOT NULL,
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
  interval_id INT NOT NULL,
  incoming INT UNSIGNED,
  outgoing INT UNSIGNED,
  PRIMARY KEY (byte_count_id)
  UNIQUE KEY (host_id, interval_id)
);

CREATE TABLE IF NOT EXISTS byte_count_intervals
(
  interval_id INT NOT NULL AUTO_INCREMENT,
  end_time DATETIME NOT NULL,
  PRIMARY KEY (interval_id),
  UNIQUE KEY (end_time)
);

CREATE TABLE IF NOT EXISTS globals
(
  name VARCHAR(255) NOT NULL,
  value TEXT,
  PRIMARY KEY (name)
);

INSERT INTO globals (name, value) VALUES ('blackout', NULL);
INSERT INTO globals (name, value) VALUES ('blackout_message', '<html>
<head><title>BLOCKED</title></head>
<body>
<h1>Blocked</h1>
<p>As of 2130 31 Aug 2005, blackout is in effect.</p>
<p>The internet will be down until the blackout is lifted.</p>
</body>
</html>');
