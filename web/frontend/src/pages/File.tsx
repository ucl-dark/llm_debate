import useHideAnswers from "../hooks/useHideAnswers";
import { useLoaderData } from "react-router-dom";
import Link from "../components/Link";

export async function fileLoader({ params }) {
  try {
    const response = await fetch(`/api/files/${params.path_hash}`);
    const file = await response.json();
    return { file };
  } catch (error) {
    console.error("Error:", error);
  }
}

function Row({ row, hideAnswers, file }) {
  return (
    <Link
      to={`/files/${file.path_hash.slice(0, 8)}/row/${row.row_number}`}
      className="px-4 py-2 flex  justify-between flex-row hover:bg-gray-100 hover:cursor-pointer"
    >
      <div className="flex flex-col">
        <div className="">
          <span>{row.question.question_text}</span>
        </div>
        <div className="">
          {!hideAnswers && (
            <>
              <div className="text-sm">
                <span> ✅ </span>
                <span>{row.question.correct_answer}</span>
              </div>
              <div className="text-sm">
                <span> ❌ </span>
                <span>{row.question.incorrect_answer}</span>
              </div>
            </>
          )}
        </div>
      </div>
      {!hideAnswers && (
        <div className="flex items-center px-4 whitespace-nowrap">
          {`⚖️ ${row.is_judgement_correct ? 1 : 0}/${1}`}
        </div>
      )}
    </Link>
  );
}

function File() {
  const { file } = useLoaderData();
  const [getHideAnswers] = useHideAnswers();
  const hideAnswers = getHideAnswers();
  const percentageCorrect =
    (file.rows.filter((row) => row.is_judgement_correct === true).length /
      file.rows.length) *
    100;
  return (
    <div>
      <div className="my-2 py-2 border-b-gray-700 flex justify-between px-4 w-full">
        <span className="">{`${file.path} - ${
          file.rows?.length || 0
        } debates `}</span>
        {!hideAnswers && (
          <span>{`${Math.round(percentageCorrect)}% judgements correct`}</span>
        )}
      </div>
      {file.rows && file.rows.length && (
        <ul className="divide-y divide-gray-200">
          {file.rows.map((row) => (
            <Row key={row.row_number} row={row} hideAnswers={hideAnswers} file={file} />
          ))}
        </ul>
      )}
    </div>
  );
}

export default File;
