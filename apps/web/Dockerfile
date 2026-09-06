FROM node:22-bookworm-slim@sha256:83f487e0a63425e5b4d146fb5e5be574bcbe1b7b843d3ebafdd95eaf7767a7e5
WORKDIR /app
ENV NEXT_TELEMETRY_DISABLED=1 API_ORIGIN=http://api:8010
COPY package.json package-lock.json ./
COPY apps/web/package.json apps/web/package.json
RUN npm ci --ignore-scripts --no-audit --no-fund
COPY apps/web apps/web
RUN npm run build:web
RUN chown -R node:node /app/apps/web/.next
EXPOSE 3000
USER node
CMD ["npm", "run", "start", "--workspace", "apps/web"]
