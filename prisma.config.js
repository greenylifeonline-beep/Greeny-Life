module.exports = {
  schema: "./prisma/schema.prisma",
  datasource: {
    url: "postgresql://postgres:postgres@localhost:5432/greeny_life?schema=public",
  },
};

