# =============================================================================
# Abhinav Group — AI Gmail Intelligence Assistant
# Frontend Dockerfile — Multi-stage Build
# =============================================================================

# --- Base Stage (Node environment) ---
FROM node:20-alpine AS base
WORKDIR /app
COPY package.json ./
RUN npm install

# --- Development Stage (Hot-reloading Dev Server) ---
FROM base AS development
COPY . .
EXPOSE 3000
CMD ["npm", "run", "dev", "--", "--host", "0.0.0.0"]

# --- Build Stage (Production Bundling) ---
FROM base AS build
COPY . .
RUN npm run build

# --- Production Stage (Nginx Webserver) ---
FROM nginx:alpine AS production
COPY --from=build /app/dist /usr/share/nginx/html
COPY nginx.conf /etc/nginx/conf.d/default.conf
EXPOSE 3000
CMD ["nginx", "-g", "daemon off;"]
