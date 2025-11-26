# Expose your local JobHunter to the internet
# This allows the Vercel mobile app to send commands to your desktop

## Option 1: Ngrok (Easiest - Free tier available)

1. Install ngrok:
   ```bash
   brew install ngrok
   ```

2. Start ngrok tunnel to your dashboard:
   ```bash
   ngrok http 5002
   ```

3. Copy the public URL (e.g., https://abc123.ngrok.io)

4. Set it as DESKTOP_URL environment variable in Vercel:
   - Go to Vercel project settings
   - Environment Variables
   - Add: DESKTOP_URL = https://abc123.ngrok.io

## Option 2: Tailscale (Better security - always free)

1. Install Tailscale:
   ```bash
   brew install tailscale
   ```

2. Start Tailscale and get your machine's Tailscale IP

3. Your dashboard will be accessible at: http://<tailscale-ip>:5002

4. Set DESKTOP_URL in Vercel to your Tailscale URL

## Option 3: Cloudflare Tunnel (Enterprise option)

Free and permanent URL, but slightly more setup.

## Security Note:
Ngrok URLs are public. Anyone with the URL can access your dashboard.
For better security, add authentication or use Tailscale.
