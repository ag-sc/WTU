CREATE TABLE `resource` (
	mention TEXT NOT NULL,
	uri TEXT NOT NULL,
	frequency INTEGER NOT NULL,
	language TEXT NOT NULL
);

CREATE INDEX idx_resource_mention ON `resource` (mention);
CREATE INDEX idx_resource_language ON `resource` (language);
