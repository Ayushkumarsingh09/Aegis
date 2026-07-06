FROM node:20-alpine AS build
WORKDIR /app
COPY portal/package.json portal/package-lock.json* ./
RUN npm install
COPY portal/ .
ARG VITE_EXCHANGE_URL=/exchange-api
ARG VITE_QUANT_URL=/quant-api
ARG VITE_EXCHANGE_DASH=http://localhost:4000
ARG VITE_QUANT_DASH=http://localhost:4100
RUN npm run build

FROM nginx:alpine
COPY portal/docker/nginx.conf /etc/nginx/conf.d/default.conf
COPY --from=build /app/dist /usr/share/nginx/html
EXPOSE 80
CMD ["nginx", "-g", "daemon off;"]
