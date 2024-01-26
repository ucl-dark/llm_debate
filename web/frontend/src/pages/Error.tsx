import { useRouteError } from "react-router-dom";
import { datadogRum } from "@datadog/browser-rum";

function ErrorPage() {
  let error = useRouteError();
  if (error) {
    datadogRum.addError(error, {
      errorInfo: error,
    });
  }

  return (
    <div className="min-h-screen flex items-center justify-center bg-gray-100">
      <div className="bg-white p-8 rounded-lg shadow-md w-full max-w-lg">
        <h1 className="text-2xl font-semibold mb-8 text-red-600">
          Oops! An error occurred.
        </h1>
        <p className="text-gray-700 mb-8 font-bold">{error?.message}</p>
        <a href="/" className="text-blue-500 hover:underline">
          Go back to home
        </a>
      </div>
    </div>
  );
}

export default ErrorPage;
