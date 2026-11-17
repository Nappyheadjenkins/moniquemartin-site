export default function (eleventyConfig) {
  // Styles, scripts, fonts and images copied from the old WordPress site.
  eleventyConfig.addPassthroughCopy("src/wp-content");
  eleventyConfig.addPassthroughCopy("src/wp-includes");
  eleventyConfig.addPassthroughCopy("src/fonts");
  eleventyConfig.addPassthroughCopy({ "src/static": "/" });

  return {
    dir: { input: "src", output: "_site" },
    // Pages are plain HTML taken from the old site; don't treat {{ }} in them as template code.
    htmlTemplateEngine: false,
  };
}
