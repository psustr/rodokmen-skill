// Příběhy webu: data/pribehy/*.md a starý data/pribeh.md, převedené `npm run data` do src/generated/pribehy/<slug>.md.
// Jeden příběh je na /pribehy/ (jako do verze 0.5.2); víc příběhů: /pribehy/ je rozcestník a každý má /pribehy/<slug>/.
import site from '../data/site.json';

const files = import.meta.glob('../generated/pribehy/*.md', { eager: true });
const bySlug = Object.fromEntries(Object.entries(files).map(([path, mod]) => [path.split('/').pop().replace(/\.md$/, ''), mod]));

export const stories = (site.stories ?? [])
  .filter((s) => bySlug[s.slug])
  .map((s) => {
    const { Content, frontmatter: fm = {} } = bySlug[s.slug];
    return { ...s, Content, title: fm.title || 'Příběh', lead: fm.lead || '' };
  });
/** Víc příběhů = rozcestník na /pribehy/. */
export const manyStories = stories.length > 1;
export const storyHref = (s) => (manyStories ? `/pribehy/${s.slug}/` : '/pribehy/');
