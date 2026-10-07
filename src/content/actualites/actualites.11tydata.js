// Actualités : URL historique /<slug>/ (à la racine, comme sur WordPress) conservée
export default {
  layout: "layouts/article.njk",
  eleventyComputed: {
    permalink: (d) => (d.published === false ? false : `/${d.slug}/`),
  },
};
