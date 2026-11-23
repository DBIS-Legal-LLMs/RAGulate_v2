# Frontend/Dockerfile — production image of the Next.js app.
FROM node:22-alpine AS build
WORKDIR /app
RUN corepack enable && corepack prepare pnpm@9.15.9 --activate
COPY package.json pnpm-lock.yaml ./
RUN pnpm install --frozen-lockfile
COPY . .

# NEXT_PUBLIC_* values are compiled into the JavaScript at build time.
ARG NEXT_PUBLIC_AUTH_SERVICE_URL=http://localhost:8100
ARG NEXT_PUBLIC_API_BACKEND=http://localhost:8000
# Version set by CI (e.g. 1.2.3); shown in the sidebar footer as v1.2.3. Empty: package.json version.
ARG APP_VERSION=
ENV NEXT_PUBLIC_AUTH_SERVICE_URL=$NEXT_PUBLIC_AUTH_SERVICE_URL \
    NEXT_PUBLIC_API_BACKEND=$NEXT_PUBLIC_API_BACKEND \
    APP_VERSION=$APP_VERSION
RUN pnpm build

FROM node:22-alpine AS runtime
WORKDIR /app
ENV NODE_ENV=production
RUN corepack enable && corepack prepare pnpm@9.15.9 --activate
COPY --from=build /app/package.json /app/pnpm-lock.yaml ./
RUN pnpm install --frozen-lockfile --prod
COPY --from=build /app/.next ./.next
COPY --from=build /app/public ./public
COPY --from=build /app/next.config.mjs ./
EXPOSE 3000
CMD ["pnpm", "start"]
