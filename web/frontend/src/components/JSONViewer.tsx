export default function JSONViewer({
  content,
  truncate = [],
}: {
  content: string;
  truncate?: string[];
}) {
  let formattedString: string;
  let parsedContent: any;
  try {
    parsedContent = JSON.parse(content);
  } catch (e) {}

  if (parsedContent) {
    // if dealing with a json string, show it in a nicely formatted way
    const parsedContent = JSON.parse(content);
    truncate.forEach((key) => {
      if (parsedContent[key]) {
        parsedContent[key] = "<TRUNCATED>";
      }
    });
    formattedString = JSON.stringify(parsedContent, null, 4);
  } else {
    formattedString = content;
  }

  formattedString = formattedString
    .split("\\n\\n")
    .join("\n")
    .split("\\n")
    .join("\n")
    .split('\\"')
    .join('"');

  const formattedHtml = formattedString.split("\n").map((line, index) => (
    <span key={index}>
      {line}
      <br />
    </span>
  ));
  return (
    <div className="">
      <div>
        <div className="flex w-full">
          <div className="py-2 whitespace-pre-wrap w-full px-4 justify-center flex flex-col">
            {formattedHtml}
          </div>
        </div>
      </div>
    </div>
  );
}
