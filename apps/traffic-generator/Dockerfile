FROM alpine:3.20
RUN apk add --no-cache curl
WORKDIR /app
COPY traffic-gen.sh .
RUN chmod +x traffic-gen.sh
USER nobody
ENTRYPOINT ["/app/traffic-gen.sh"]
