import { FormEvent, useState } from "react";
import Input from "../components/Input";
import Button from "../components/Button";
import { useSearchParams } from "react-router-dom";

export default function Login() {
  const [userName, setUserName] = useState("");
  const [error, setError] = useState("");
  const [searchParams] = useSearchParams();

  const logoutSuccessful = searchParams.get("logout");
  const loginRequired = searchParams.get("loginRequired")
  async function login(e: FormEvent<HTMLFormElement>) {
    e.preventDefault()
    setError("");
    if (!userName) {
      setError("Please provide a user name.");
      return;
    }

    try {
      const response = await fetch(`/api/users/login`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          user_name: userName,
        }),
      });
      if (response.status === 404) {
        setError(`User ${userName} not found.`);
        return;
      } else if (!response.ok) {
        throw new TypeError(`Status ${response.status}`);
      } else {
        // cookie is set by backend on successful login, so we can just go to home
        window.location.href = "/";
      }
    } catch (error) {
      setError("Error logging in.");
      console.error(error);
      return;
    }
  }

  return (
    <div className="px-32 mt-32">
      <form onSubmit={login}>
        <Input
          value={userName}
          error={error}
          label="User name"
          onChange={(e) => setUserName(e.target.value)}
        />
        <Button type="submit" className="mt-8">
          Log in
        </Button>
      </form>
      {logoutSuccessful && (
        <div className="fixed bottom-8 rounded-full left-16 right-16 bg-blue-200 text-gray-900 text-center py-2 z-50">
          You have successfully logged out.
        </div>
      )}
      {loginRequired && (
        <div className="fixed bottom-8 rounded-full left-16 right-16 bg-blue-200 text-gray-900 text-center py-2 z-50">
          You must be logged in to view this page.
        </div>
      )}
    </div>
  );
}
