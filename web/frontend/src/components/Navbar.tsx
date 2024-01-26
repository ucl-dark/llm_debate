import Link from "../components/Link";
import { useUser, useLogout } from "../hooks/userProvider";
import { Switch } from "@headlessui/react";
import useHideAnswers from "../hooks/useHideAnswers";
import Logo from "../assets/debate.png";
import { useLocation, useNavigate } from "react-router-dom";
import Button from "./Button";

function classNames(...classes) {
  return classes.filter(Boolean).join(" ");
}

function UserNav() {
  const { user } = useUser();
  const logout = useLogout();
  const navigate = useNavigate();
  let element;

  if (user) {
    element = (
      <>
        <div className="mr-4 ">
          Logged in as <span className="font-bold">{user.user_name}</span>
        </div>
        <Button onClick={logout} variant="secondary">
          Log out
        </Button>
      </>
    );
  } else {
    element = (
      <>
        <Button onClick={() => navigate("/login")} variant="secondary">
          Log in
        </Button>
      </>
    );
  }

  return <div className=" flex flex-row items-center ml-8">{element}</div>;
}

function Navbar() {
  const location = useLocation();
  const [getHideAnswers, toggleHideAnswers] = useHideAnswers();
  const hideAnswers = getHideAnswers();
  const { user } = useUser();

  function linkClasses({
    exact,
    startsWith,
  }: {
    exact?: string;
    startsWith?: string;
  }) {
    const active =
      (exact && exact == location.pathname) ||
      (startsWith && location.pathname.startsWith(startsWith));
    return classNames(
      "inline-flex items-center px-1 pt-1 text-sm font-medium text-gray-900 border-b-2",
      active ? "border-indigo-500" : "border-transparent hover:border-gray-300",
    );
  }

  return (
    <div className="px-4 sm:px-6 lg:px-8">
      <div className="flex h-16 justify-between">
        <div className="flex">
          <div className="flex flex-shrink-0 items-center">
            <img className=" h-8 w-auto block" src={Logo} />
          </div>
          {user && (
            <div className="hidden sm:ml-6 sm:flex sm:space-x-8">
              {user.admin && (
                <>
                  <Link
                    to={"/files"}
                    className={linkClasses({
                      exact: "/",
                      startsWith: "/files",
                    })}
                  >
                    Files
                  </Link>
                  <Link
                    to={"/playground"}
                    className={linkClasses({ startsWith: "/playground" })}
                  >
                    Playground
                  </Link>
                </>
              )}
              <Link
                to={"/experiments"}
                className={linkClasses({ startsWith: "/experiments" })}
              >
                Experiments
              </Link>
            </div>
          )}
        </div>
        <div className="flex flex-row items-center">
          {!location.pathname.includes("login") && (
            <Switch.Group as="div" className="px-2 py-2 flex items-center">
              <Switch.Label as="span" className="mr-3 text-sm">
                <span className="font-medium text-gray-900">Hide answers</span>
              </Switch.Label>
              <Switch
                checked={hideAnswers}
                onChange={toggleHideAnswers}
                className={classNames(
                  hideAnswers ? "bg-blue-600" : "bg-gray-200",
                  "relative inline-flex h-6 w-11 flex-shrink-0 cursor-pointer rounded-full border-2 border-transparent transition-colors duration-200 ease-in-out focus:outline-none focus:ring-2 focus:ring-blue-600 focus:ring-offset-2",
                )}
              >
                <span
                  aria-hidden="true"
                  className={classNames(
                    hideAnswers ? "translate-x-5" : "translate-x-0",
                    "pointer-events-none inline-block h-5 w-5 transform rounded-full bg-white shadow ring-0 transition duration-200 ease-in-out",
                  )}
                />
              </Switch>
            </Switch.Group>
          )}
          <UserNav />
        </div>
      </div>
    </div>
  );
}

export default Navbar;
