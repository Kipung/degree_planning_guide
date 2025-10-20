FROM node:20-alpine
WORKDIR /app

# deps layer (cache)
COPY package*.json ./
RUN npm ci

# app layer
COPY . .

EXPOSE 5173
CMD ["npm", "run", "dev", "--", "--host", "--port", "5173"]