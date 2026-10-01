export default async function handler(req, res) {
  res.setHeader('Access-Control-Allow-Origin', '*');
  res.setHeader('Access-Control-Allow-Methods', 'GET, POST, OPTIONS');
  res.setHeader('Access-Control-Allow-Headers', 'Content-Type');

  if (req.method === 'OPTIONS') {
    res.status(200).end();
    return;
  }

  const { tag, courseId, categoryId } = req.query;
  const targetUrl = 'https://bridgetosuccess.learncentre.tech/public/study_api_sprint13_security_promo/';
  
  const postData = new URLSearchParams({
    userId: '12644',
    tag: tag || '',
  });

  if (courseId) postData.append('courseId', courseId);
  if (categoryId) postData.append('categoryId', categoryId);
  if (tag === 'allCourses') {
    postData.append('isEBook', '0');
  }

  try {
    const response = await fetch(targetUrl, {
      method: 'POST',
      headers: {
        'User-Agent': 'okhttp/5.3.2',
        'Content-Type': 'application/x-www-form-urlencoded',
      },
      body: postData.toString(),
    });

    const data = await response.json();
    res.status(200).json(data);
  } catch (error) {
    res.status(500).json({ success: 0, error: error.message });
  }
}
