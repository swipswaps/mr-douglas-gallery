const express = require('express');
const cors = require('cors');
const sharp = require('sharp');
const PDFDocument = require('pdfkit');
const fs = require('fs');
const path = require('path');

const app = express();
const PORT = process.env.PORT || 3000;

app.use(cors());
app.use(express.json({ limit: '50mb' }));
app.use('/media', express.static(process.env.MEDIA_ROOT || './media'));

app.post('/api/export/pdf', async (req, res) => {
  try {
    const { items, pageWidth, pageHeight, backgroundColor } = req.body;
    const doc = new PDFDocument({
      size: [pageWidth || 1920, pageHeight || 1080],
      margins: { top: 0, bottom: 0, left: 0, right: 0 }
    });
    const buffers = [];
    doc.on('data', buffers.push.bind(buffers));
    doc.on('end', () => {
      const pdfData = Buffer.concat(buffers);
      res.setHeader('Content-Type', 'application/pdf');
      res.setHeader('Content-Disposition', 'attachment; filename=layout.pdf');
      res.send(pdfData);
    });

    if (backgroundColor && backgroundColor !== 'transparent') {
      doc.rect(0, 0, pageWidth, pageHeight).fill(backgroundColor);
    }

    for (const item of items) {
      if (item.type === 'image' && item.post?.media?.[0]) {
        const imgPath = path.join(process.env.MEDIA_ROOT || './media', item.post.media[0]);
        if (fs.existsSync(imgPath)) {
          doc.image(imgPath, item.x, item.y, { width: item.width, height: item.height });
        }
      }
    }
    doc.end();
  } catch (error) {
    console.error('PDF export error:', error);
    res.status(500).json({ error: 'Failed to generate PDF' });
  }
});

app.listen(PORT, () => {
  console.log(`Backend running on port ${PORT}`);
});
