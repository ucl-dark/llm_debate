import Cookie from "js-cookie";
import React, {
  createContext,
  useContext,
  useState,
  useEffect,
  ReactNode,
} from "react";
import { User } from "../utils/types";
import { useNavigate } from "react-router-dom";
import { datadogRum } from "@datadog/browser-rum";

const USER_ID_COOKIE = "user_id";
const USER_LOCAL_STORAGE = "user";

type UserContextType = {
  user: User | null;
  loading: boolean;
  setUser: React.Dispatch<React.SetStateAction<User | null>>;
};

const defaultUserContext: UserContextType = {
  user: null,
  loading: true,
  setUser: () => {},
};

const UserContext = createContext<UserContextType>(defaultUserContext);

async function fetchUserFromServer(userId: string) {
  try {
    const response = await fetch(`/api/users/${userId}`);

    if (!response.ok) {
      throw new Error(`HTTP error! status: ${response.status}`);
    }

    const data = await response.json();
    return data;
  } catch (error) {
    console.error("Failed to fetch user:", error);
    return null;
  }
}

export async function getCurrentUser() {
  const userId = Cookie.get(USER_ID_COOKIE);

  if (!userId) {
    return null;
  }

  let userInLocalStorage: User = JSON.parse(
    localStorage.getItem(USER_LOCAL_STORAGE) || "null",
  );

  if (userInLocalStorage) {
    datadogRum.setUser({
      id: String(userInLocalStorage.id),
      name: userInLocalStorage.user_name,
    });
    return userInLocalStorage;
  }

  const userFromServer: User = await fetchUserFromServer(userId);

  if (userFromServer) {
    localStorage.setItem(USER_LOCAL_STORAGE, JSON.stringify(userFromServer));
    datadogRum.setUser({
      id: String(userFromServer.id),
      name: userFromServer.user_name,
    });

    return userFromServer;
  }

  return null;
}

export enum AuthRequirement {
  None,
  User,
  Admin,
}

export const useUser = (
  authRequirement: AuthRequirement = AuthRequirement.None,
) => {
  const context = useContext(UserContext);
  const navigate = useNavigate();

  if (!context) {
    throw new Error("useUser must be used within a UserProvider");
  }

  const { user, loading } = context;

  useEffect(() => {
    if (loading) {
      return;
    }

    switch (authRequirement) {
      case AuthRequirement.User:
        if (!user) {
          navigate("/login?loginRequired=true");
        }
        break;
      case AuthRequirement.Admin:
        if (!user) {
          navigate("/login?loginRequired=true");
        } else if (!user.admin) {
          navigate("/admins_only");
        }
        break;
      default:
        break;
    }
  }, [user, authRequirement, history, loading]);

  return context;
};

export const UserProvider = ({ children }: { children: ReactNode }) => {
  const [user, setUser] = useState<User | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const initializeUser = async () => {
      try {
        const currentUser = await getCurrentUser();
        setUser(currentUser);
      } finally {
        setLoading(false);
      }
    };

    initializeUser();
  }, []);

  return (
    <UserContext.Provider value={{ user, setUser, loading }}>
      {children}
    </UserContext.Provider>
  );
};

export function useLogout() {
  const { setUser } = useUser();

  const logout = () => {
    // Delete the user cookie
    Cookie.remove(USER_ID_COOKIE);

    // Remove the user from local storage
    localStorage.removeItem(USER_LOCAL_STORAGE);

    // Remove the user from React context
    setUser(null);
    datadogRum.setUser(null);

    // Redirect to /login with a logout flag
    window.location.href = "/login?logout=true";
  };

  return logout;
}
