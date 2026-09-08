FROM oven/bun:1.3.10 AS bun
FROM node:22-bookworm-slim@sha256:83f487e0a63425e5b4d146fb5e5be574bcbe1b7b843d3ebafdd95eaf7767a7e5
COPY --from=bun /usr/local/bin/bun /usr/local/bin/bun
WORKDIR /app
ENV NEXT_TELEMETRY_DISABLED=1 API_ORIGIN=http://api:8010
COPY package.json bun.lock ./
COPY apps/web/package.json apps/web/package.json
RUN bun install --frozen-lockfile --ignore-scripts
COPY apps/web apps/web
RUN bun run build:web
RUN chown -R node:node /app/apps/web/.next
EXPOSE 3000
USER node
WORKDIR /app/apps/web
CMD ["bun", "run", "start"]
