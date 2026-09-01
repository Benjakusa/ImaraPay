FROM node:20-alpine AS dev

WORKDIR /app

# Install deps first (cached layer)
COPY package.json package-lock.json ./
RUN npm ci

# Copy source (overridden by volume mount in dev)
COPY . .

EXPOSE 5173

# Vite must bind to 0.0.0.0 so Docker port mapping works
CMD ["npm", "run", "dev", "--", "--host", "0.0.0.0"]
