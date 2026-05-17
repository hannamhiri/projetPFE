FROM cubejs/cube:latest

RUN node -e " \
const fs = require('fs'); \
const bq = '/cube/node_modules/@cubejs-backend/schema-compiler/dist/src/adapter/BaseQuery.js'; \
let c = fs.readFileSync(bq, 'utf8'); \
c = c.replace(\"string: 'STRING'\", \"string: 'String'\"); \
fs.writeFileSync(bq, c); \
const chq = '/cube/node_modules/@cubejs-backend/schema-compiler/dist/src/adapter/ClickHouseQuery.js'; \
let c2 = fs.readFileSync(chq, 'utf8'); \
c2 = c2.replace('castToString(sql) {', 'castToString(sql) {\n        if (sql === \"NULL\") return \"CAST(null as Nullable(String))\";\n'); \
fs.writeFileSync(chq, c2); \
console.log('Patches OK'); \
"