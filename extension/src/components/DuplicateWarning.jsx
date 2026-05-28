export default function DuplicateWarning({ duplicates }) {
  if (!duplicates?.length) return null;

  return (
    <div className="duplicate-warning">
      <strong>Possible duplicates found</strong>
      <ul>
        {duplicates.map((d) => (
          <li key={d.id}>
            <a href={d.url} target="_blank" rel="noreferrer">
              #{d.id}
            </a>
          </li>
        ))}
      </ul>
    </div>
  );
}
