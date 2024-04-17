# Build Stage
FROM node:20-alpine AS BUILD_IMAGE
WORKDIR /app
COPY yarn.lock package*.json ./
RUN yarn install --frozen-lockfile
COPY . .
RUN yarn run build

# Production Stage
ENV NODE_ENV=production
EXPOSE 3000
CMD ["yarn", "start"]