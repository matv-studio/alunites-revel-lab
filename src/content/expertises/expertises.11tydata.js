// Expertises : URL historique /expertise/<slug>/ conservée
export default {
  layout: "layouts/expertise.njk",
  eleventyComputed: {
    permalink: (d) => `/expertise/${d.slug}/`,
  },
};
