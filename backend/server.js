const express = require('express');
const cors = require('cors');
const sqlite3 = require('sqlite3').verbose();
const path = require('path');

const app = express();
const PORT = process.env.PORT || 3000;

app.use(cors());
app.use(express.json());

const mediaRoot = process.env.MEDIA_ROOT || '/data/instagram_sav_a_dc3_extracted';
app.use('/media', express.static(mediaRoot));

const dbPath = process.env.DB_PATH || './db/posts.db';
const db = new sqlite3.Database(dbPath);

db.serialize(() => {
  db.run(`CREATE TABLE IF NOT EXISTS posts (
    id TEXT PRIMARY KEY,
    date TEXT,
    caption TEXT,
    media TEXT,
    comments TEXT
  )`);
});

app.get('/api/posts', (req, res) => {
  db.all('SELECT * FROM posts', (err, rows) => {
    if (err) return res.status(500).json({ error: err.message });
    const posts = rows.map(row => ({
      ...row,
      media: JSON.parse(row.media),
      comments: JSON.parse(row.comments),
    }));
    res.json(posts);
  });
});

app.listen(PORT, () => {
  console.log(`Backend running on http://localhost:${PORT}`);
});
