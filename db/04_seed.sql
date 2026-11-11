-- Rerunnable seed: existing plan rows and edits are preserved.
INSERT INTO plan (name, monthly_price, max_profiles, max_streams, max_quality) VALUES
    ('Student', 99, 1, 1, 'HD'),
    ('Basic', 199, 1, 1, 'HD'),
    ('Duo', 349, 2, 2, 'HD'),
    ('Premium', 499, 1, 3, '4K'),
    ('Family', 649, 4, 4, '4K')
ON CONFLICT (name) DO NOTHING;
