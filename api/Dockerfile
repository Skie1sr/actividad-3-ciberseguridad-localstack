FROM node:24-alpine
ENV NODE_ENV=production
WORKDIR /app
COPY package*.json ./
RUN npm ci --omit=dev && npm cache clean --force \
    && apk upgrade --no-cache zlib \
    && rm -rf /usr/local/lib/node_modules/npm \
       /usr/local/bin/npm /usr/local/bin/npx
COPY --chown=node:node server.js ./
USER node
EXPOSE 3000
CMD ["node", "server.js"]
