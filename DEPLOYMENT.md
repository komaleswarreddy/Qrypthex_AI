# 🚀 Deployment Guide for QubitScope on Streamlit Cloud

## 📋 Prerequisites

- GitHub account
- Streamlit Cloud account (free at [share.streamlit.io](https://share.streamlit.io))
- Groq API key (for AI explanations) — free at [console.groq.com/keys](https://console.groq.com/keys)

## 🔧 Step-by-Step Deployment

### 1. **Prepare Your Local Repository**

```bash
# Initialize git if not already done
git init

# Add all files
git add .

# Commit changes
git commit -m "Initial commit: QubitScope Quantum Visualizer"

# Create and switch to main branch
git branch -M main
```

### 2. **Push to GitHub**

```bash
# Add your GitHub repository as remote
git remote add origin https://github.com/YOUR_USERNAME/YOUR_REPO_NAME.git

# Push to GitHub
git push -u origin main
```

### 3. **Deploy on Streamlit Cloud**

1. **Visit [share.streamlit.io](https://share.streamlit.io)**
2. **Sign in with your GitHub account**
3. **Click "New app"**
4. **Fill in the deployment form:**
   - **Repository**: Select your GitHub repository
   - **Branch**: `main`
   - **Main file path**: `app.py`
   - **App URL**: Choose a custom URL (optional)

### 4. **Configure Environment Variables**

**Critical Step**: You must add your Groq API key to Streamlit secrets.

1. **In Streamlit Cloud dashboard, go to your app's "Settings"**
2. **Click on "Secrets"**
3. **Add this configuration:**

```toml
GROQ_API_KEY = "gsk_your-actual-api-key-here"
```

**⚠️ Important**: Replace `gsk_your-actual-api-key-here` with your real Groq API key.

### 5. **Deploy and Test**

1. **Click "Deploy!"**
2. **Wait for deployment to complete** (usually 2-5 minutes)
3. **Test your app** by visiting the provided URL

## 🔐 Security Considerations

- **Never commit API keys** to your repository
- **Use Streamlit secrets** for sensitive configuration
- **The `.gitignore` file** excludes sensitive files
- **API keys are encrypted** in Streamlit Cloud

## 📊 App Features After Deployment

Your deployed app will include:

- ✅ **Quantum circuit visualization** with Bloch spheres
- ✅ **Interactive timeline** for step-by-step analysis
- ✅ **AI-powered explanations** (Kid+Pro hybrid mode)
- ✅ **Noise modeling** and comparison
- ✅ **Measurement simulation**
- ✅ **Entanglement analysis**
- ✅ **Export functionality** (OpenQASM, CSV, JSON)

## 🚨 Troubleshooting

### **Common Issues:**

1. **"Module not found" errors**
   - Ensure all dependencies are in `requirements.txt`
   - Check that Streamlit Cloud supports the package versions

2. **API key errors**
   - Verify the secret is correctly set in Streamlit Cloud
   - Check the secret name matches exactly: `GROQ_API_KEY`

3. **Deployment fails**
   - Check the deployment logs in Streamlit Cloud
   - Ensure `app.py` is the main file
   - Verify all imports are available

### **Performance Tips:**

- **Large quantum circuits** (>6 qubits) may be slow
- **AI explanations** depend on API response time
- **Use caching** for expensive calculations (already implemented)

## 🔄 Updating Your App

```bash
# Make changes locally
git add .
git commit -m "Update: [describe changes]"
git push origin main

# Streamlit Cloud automatically redeploys on push
```

## 📱 Accessing Your App

- **Public URL**: `https://your-app-name.streamlit.app`
- **Custom domain**: Available in Streamlit Cloud settings
- **Mobile responsive**: Works on all devices

## 🎯 Next Steps

After successful deployment:

1. **Share your app** with the quantum computing community
2. **Monitor usage** in Streamlit Cloud dashboard
3. **Collect feedback** from users
4. **Iterate and improve** based on usage patterns

---

**🎉 Congratulations!** Your QubitScope quantum visualizer is now live on Streamlit Cloud and accessible to users worldwide!
