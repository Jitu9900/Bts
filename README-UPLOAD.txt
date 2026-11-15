BRIDGE TO SUCCESS - GITHUB UPLOAD

Upload these paths into the ROOT of your existing GitHub repository (keep the folder structure):
  index.html
  vercel.json
  api/services.js

Do NOT upload services.php to Vercel: Vercel does not execute PHP files as serverless functions.
Do NOT delete your other existing project files unless you know they are unused.

After commit/push to the connected Vercel production branch, Vercel should build a deployment.
The frontend now calls /api/services. The API supports courses, content, formats, stream, video download, and PDF download.

Notes:
- Course images and PDF preview still use the existing bridgetosuccess.learncentre.tech asset host.
- The upstream course API and video download provider must remain available. If either provider blocks Vercel or changes its API, those functions can still fail; this package cannot override provider-side restrictions.
- Check the Vercel deployment logs if the build fails. The API uses Node.js built-in fetch and the Node stream module; no npm packages are required.
