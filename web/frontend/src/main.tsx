import ReactDOM from "react-dom/client";
import File, { fileLoader } from "./pages/File.tsx";
import Row, { rowLoader } from "./pages/Row.tsx";
import App from "./App.tsx";
import "./index.css";
import "./styles.css";
import { createBrowserRouter, RouterProvider} from "react-router-dom";
import Files, { filesLoader } from "./pages/Files.tsx";
import { debateLoader} from "./utils/loaders.ts";
import PlaygroundDebates, {
  playgroundDebatesLoader,
} from "./pages/Playground/Debates.tsx";
import PlaygroundDebate from "./pages/Playground/Debate.tsx";
import Error from "./pages/Error.tsx";
import ExperimentDebates, {
  experimentDebatesLoader,
} from "./pages/Experiments/Debates.tsx";
import ExperimentDebate from "./pages/Experiments/Debate.tsx";
import Login from "./pages/Login.tsx";
import RootRedirect from "./pages/RootRedirect.tsx";
import AdminsOnly from "./pages/AdminsOnly.tsx";
import { datadogRum } from '@datadog/browser-rum';

const env = import.meta.env.VITE_APP_ENV;
if (!env) {
  console.warn("Datadog environment not set!")
}

datadogRum.init({
    applicationId: '5fd45f08-2f9a-43be-ae1d-ceaee01917d3',
    clientToken: 'pub4a9609b3cd3691b1d18bb31136ee3550',
    site: 'datadoghq.com',
    service: 'debate-ui',
    env: env,
    sessionSampleRate: 100,
    sessionReplaySampleRate: 100,
    trackUserInteractions: true,
    trackResources: true,
    trackLongTasks: true,
    defaultPrivacyLevel: 'allow',
});

const router = createBrowserRouter([
  {
    path: "/",
    element: <App />,
    children: [
      { index: true, element: <RootRedirect /> },
      { path: "/login", element: <Login /> },
      { path: "/admins_only", element: <AdminsOnly /> },
      {
        path: "/files",
        element: <Files />,
        loader: filesLoader,
      },
      {
        path: "/files/:path_hash",
        element: <File />,
        loader: fileLoader,
      },
      {
        path: "/files/:path_hash/row/:row_number",
        element: <Row />,
        loader: rowLoader,
      },
      {
        path: "/playground",
        element: <PlaygroundDebates />,
        loader: playgroundDebatesLoader,
      },
      {
        path: "/playground/debates/:debate_id",
        element: <PlaygroundDebate />,
        loader: debateLoader,
      },
      {
        path: "/experiments",
        element: <ExperimentDebates />,
        loader: experimentDebatesLoader,
      },
      {
        path: "/experiments/debates/:debate_id",
        element: <ExperimentDebate />,
        loader: debateLoader,
      },
    ],
    errorElement: <Error/>

  },
]);

ReactDOM.createRoot(document.getElementById("root")!).render(
  <RouterProvider router={router} />,
);
