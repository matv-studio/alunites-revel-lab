// Projets : URL historique /project/<slug>/ conservée (SEO)
export default {
  layout: "layouts/project.njk",
  eleventyComputed: {
    permalink: (d) => (d.published === false ? false : `/project/${d.slug}/`),
  },
};
